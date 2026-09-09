"""
A q:action silently dropped most of its body.

_execute_action_body was a hand-maintained if-elif chain listing the node
types an action was allowed to contain — Redirect, Flash, Set, Python, If —
with `QueryNode: pass  # TODO` and no else at all. Consequences, reproduced:

- **q:query inside q:action did nothing.** A form handler could not write to
  the database, which is the entire point of an action. It still returned 302
  as if it had worked.
- q:mail, q:log, q:file, q:dump, q:invoke, q:llm: silently ignored.
- q:if's elseif branches were unpacked as 2-tuples from a list of DICTS, so
  iterating yielded the dict's KEYS and the literal strings "condition" and
  "body" were used as the condition and the body.

The body now goes through the same ExecutorRegistry the rest of the engine
uses, and anything genuinely unhandled is logged instead of dropped.
"""

import contextlib
import io
import logging
import sqlite3

import pytest
from flask import Flask

from quantum.core.parser import QuantumParser
from quantum.runtime.action_handler import ActionHandler
from quantum.runtime.component import ComponentRuntime


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "a.db"
    con = sqlite3.connect(str(path))
    con.execute("CREATE TABLE msg (id INTEGER PRIMARY KEY, txt TEXT)")
    con.commit()
    con.close()
    return path


@pytest.fixture
def app():
    a = Flask(__name__)
    a.secret_key = "t"
    return a


def _action_from(src):
    ast = QuantumParser().parse(src)
    return next(s for s in ast.statements if type(s).__name__ == "ActionNode")


def _run(app, runtime, action, form):
    with app.test_request_context("/x", method="POST", data=form):
        with contextlib.redirect_stdout(io.StringIO()):
            return ActionHandler(runtime).handle_action(action)


def _rows(db):
    con = sqlite3.connect(str(db))
    rows = [r[0] for r in con.execute("SELECT txt FROM msg ORDER BY id")]
    con.close()
    return rows


class TestQueryRunsInsideAnAction:
    SRC = (
        '<q:component name="F">'
        '<q:action name="salvar" method="POST">'
        '<q:param name="txt" type="string" required="true" />'
        '<q:query name="ins" datasource="a">INSERT INTO msg (txt) VALUES (:t)'
        '<q:param name="t" value="{txt}" /></q:query>'
        '<q:redirect url="/ok" flash="salvo" />'
        '</q:action></q:component>'
    )

    def test_the_row_is_actually_written(self, app, db):
        rt = ComponentRuntime(config={
            "datasources": {"a": {"driver": "sqlite", "database": str(db)}}
        })
        out = _run(app, rt, _action_from(self.SRC), {"txt": "ola mundo"})
        assert out == ("/ok", 302)
        assert _rows(db) == ["ola mundo"], "q:query inside q:action did nothing"

    def test_a_query_inside_an_if_also_runs(self, app, db):
        src = (
            '<q:component name="F">'
            '<q:action name="salvar" method="POST">'
            '<q:param name="txt" type="string" required="true" />'
            '<q:if condition="1 == 1">'
            '<q:query name="ins" datasource="a">INSERT INTO msg (txt) VALUES (:t)'
            '<q:param name="t" value="{txt}" /></q:query>'
            '</q:if>'
            '<q:redirect url="/ok" />'
            '</q:action></q:component>'
        )
        rt = ComponentRuntime(config={
            "datasources": {"a": {"driver": "sqlite", "database": str(db)}}
        })
        _run(app, rt, _action_from(src), {"txt": "aninhado"})
        assert _rows(db) == ["aninhado"]


class TestNothingIsDroppedSilently:
    def test_an_unhandled_node_is_logged(self, app, caplog):
        """There used to be no else at all."""
        from quantum.core.ast_nodes import DispatchEventNode

        rt = ComponentRuntime()
        handler = ActionHandler(rt)
        from quantum.runtime.execution_context import ExecutionContext

        with app.test_request_context("/x", method="POST"):
            with caplog.at_level(logging.WARNING, logger="quantum.action"):
                handler._execute_one(DispatchEventNode("evt"), ExecutionContext())
        assert any("no executor" in r.message for r in caplog.records)


class TestElseIfBranchesUseTheRightShape:
    def test_the_elseif_branch_fires(self, app, db):
        src = (
            '<q:component name="F">'
            '<q:action name="a" method="POST">'
            '<q:param name="n" type="integer" required="true" />'
            '<q:if condition="n == 1">'
            '<q:redirect url="/um" />'
            '<q:elseif condition="n == 2"><q:redirect url="/dois" /></q:elseif>'
            '<q:else><q:redirect url="/outro" /></q:else>'
            '</q:if>'
            '</q:action></q:component>'
        )
        rt = ComponentRuntime()
        action = _action_from(src)
        assert _run(app, rt, action, {"n": "2"})[0] == "/dois"
        assert _run(app, rt, action, {"n": "1"})[0] == "/um"
        assert _run(app, rt, action, {"n": "7"})[0] == "/outro"
