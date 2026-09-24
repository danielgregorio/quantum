"""Correct SQL was refused at parse time because of a `:` inside quotes.

The parser requires every `:name` in the SQL to have a matching `<q:param>` —
a good rule, which exists to catch the forgotten parameter. But the scan was a
`re.findall(r':([a-zA-Z_]\\w*)', sql)` over the RAW SQL, and so also over what
is inside text literals and comments:

    TO_CHAR(c.created_at, 'YYYY-MM-DD HH24:MI')   ->  found `:MI`
    SELECT x::text FROM t                         ->  found `:text`

Both forms are common SQL. The first appears in projects/blog/components/post.q,
which did not parse because of it: the file was refused with "SQL parameter(s)
:MI declared in SQL but no matching <q:param> element provided" — and there
was no parameter at all to declare. There was nothing to do but rewrite the SQL.
"""

import pytest

from quantum.core.parser import QuantumParser, QuantumParseError
from quantum.core.parsers.data.query_parser import QueryParser


class TestTheScan:
    @pytest.mark.parametrize("sql,expected", [
        # what IS a parameter
        ("SELECT * FROM t WHERE id = :id", {'id'}),
        ("INSERT INTO t (a, b) VALUES (:a, :b)", {'a', 'b'}),
        ("SELECT * FROM t WHERE a = :a AND b = :b", {'a', 'b'}),
        # what is NOT
        ("SELECT TO_CHAR(x, 'HH24:MI') FROM t", set()),
        ("SELECT TO_CHAR(x, 'YYYY-MM-DD HH24:MI:SS') FROM t", set()),
        ("SELECT x::text FROM t", set()),
        ("SELECT x::int, y::text FROM t", set()),
        ("SELECT 1 -- a comment with :notone\n", set()),
        ("SELECT 1 /* a block with :notone */", set()),
        ('SELECT "odd:column" FROM t', set()),
        ("SELECT 'a literal with ''quotes'' and :notone' FROM t", set()),
        # mixed
        ("SELECT TO_CHAR(x, 'HH24:MI') FROM t WHERE id = :id", {'id'}),
        ("SELECT x::text FROM t WHERE a = :a", {'a'}),
        ("SELECT 1 /* :no */ WHERE a = :a -- :no2\n", {'a'}),
    ])
    def test_only_the_real_parameters(self, sql, expected):
        assert QueryParser._named_params(sql) == expected


class TestThroughTheRealParser:
    def _parse(self, sql, params=''):
        source = (f'<q:component name="C">'
                  f'<q:query name="q" datasource="db">{sql}{params}</q:query>'
                  f'</q:component>')
        return QuantumParser(use_cache=False).parse(source)

    def test_a_date_format_with_a_colon_is_accepted(self):
        self._parse("SELECT TO_CHAR(c.created_at, 'YYYY-MM-DD HH24:MI') "
                    "as created_at FROM comments")

    def test_a_postgres_cast_is_accepted(self):
        self._parse("SELECT id::text FROM users")

    def test_a_real_parameter_without_a_q_param_is_STILL_refused(self):
        """The rule exists to catch the forgotten parameter; it must not vanish."""
        with pytest.raises(QuantumParseError, match=":id"):
            self._parse("SELECT * FROM t WHERE id = :id")

    def test_with_the_q_param_declared_it_passes(self):
        self._parse("SELECT * FROM t WHERE id = :id",
                    '<q:param name="id" value="1" />')

    def test_a_forgotten_parameter_next_to_a_date_format(self):
        """The mixed case: the date must not hide the missing parameter."""
        with pytest.raises(QuantumParseError, match=":user_id"):
            self._parse("SELECT TO_CHAR(x, 'HH24:MI') FROM t "
                        "WHERE user_id = :user_id")


class TestTheFileThatDidNotParse:
    def test_projects_blog_components_post_q(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        target = root / 'projects' / 'blog' / 'components' / 'post.q'
        if not target.exists():
            pytest.skip("the file is not in this checkout")
        QuantumParser(use_cache=False).parse_file(str(target))
