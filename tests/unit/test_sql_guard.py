"""
sanitize_sql was theatre: it broke legitimate queries and stopped nothing.

The old denylist matched ';.*DROP TABLE', ';.*DELETE FROM', ';.*INSERT INTO'
and 'UNION.*SELECT' against the SQL text. `.` does not match a newline, so one
line break walked past all four — while an ordinary UNION query was rejected.

It was also guarding a threat the architecture prevents by construction, which
these tests pin: node.sql is never databound, q:param values are bound by the
driver, and page/page_size are ints read from the template at parse time. So
the guard now catches the mistake people actually make instead — a databinding
placeholder written into the SQL body, which used to reach the database as
literal text and silently return nothing.
"""

import sqlite3

import pytest

from quantum.runtime.query_validators import QueryValidator, QueryValidationError


class TestLegitimateSqlIsNotBlocked:
    @pytest.mark.parametrize("sql", [
        "SELECT name FROM a UNION SELECT email FROM b",
        "SELECT a FROM t UNION ALL SELECT b FROM u",
        "INSERT INTO orders (id, total) VALUES (:id, :total)",
        "DELETE FROM users WHERE email = :email",
        "UPDATE accounts SET balance = balance - :amount WHERE id = :from_id",
        "SELECT * FROM users WHERE status = :status ORDER BY name LIMIT 10",
    ])
    def test_allowed(self, sql):
        assert QueryValidator.sanitize_sql(sql) == sql


class TestTheRealMistakeIsCaught:
    """A placeholder in the SQL body silently returned nothing. Now it says so."""

    @pytest.mark.parametrize("sql", [
        "SELECT * FROM users WHERE name = '{form.name}'",
        "SELECT * FROM t WHERE id = {query.id}",
        "SELECT * FROM t WHERE a = '{session.user}' AND b = 1",
    ])
    def test_rejected_with_a_useful_message(self, sql):
        with pytest.raises(QueryValidationError) as e:
            QueryValidator.sanitize_sql(sql)
        msg = str(e.value)
        assert "q:param" in msg
        assert ":name" in msg or "bound parameter" in msg


class TestNoInjectionPathExists:
    """The property the removed denylist was pretending to provide.

    Verified end to end rather than asserted: a databinding placeholder in the
    SQL reaches the database as literal text, so there is nothing to inject
    into. (The guard above now rejects it earlier, so this exercises the
    database layer directly.)
    """

    def test_a_bound_parameter_is_data_not_syntax(self, tmp_path):
        from quantum.runtime.database_service import DatabaseService

        db = tmp_path / "t.db"
        con = sqlite3.connect(str(db))
        con.execute("CREATE TABLE u (id INTEGER PRIMARY KEY, nome TEXT)")
        con.executemany("INSERT INTO u VALUES (?, ?)", [(1, "ana"), (2, "bob")])
        con.commit()
        con.close()

        svc = DatabaseService(local_datasources={
            "t": {"driver": "sqlite", "database": str(db)}
        })
        # The classic payload, as a bound VALUE.
        r = svc.execute_query(
            "t", "SELECT nome FROM u WHERE nome = :n", {"n": "x' OR '1'='1"}
        )
        assert r.data == [], "the payload was parsed as syntax, not compared as data"

        # And the ordinary case still works.
        r2 = svc.execute_query("t", "SELECT nome FROM u WHERE nome = :n", {"n": "ana"})
        assert [row["nome"] for row in r2.data] == ["ana"]


class TestTheDuplicateCannotDiverge:
    """core/features/query/src/query_validators.py held a stale COPY of a
    security validator that nothing imported. It re-exports now."""

    def test_both_import_paths_are_the_same_class(self):
        from quantum.core.features.query.src.query_validators import (
            QueryValidator as Copy,
        )
        assert Copy is QueryValidator
