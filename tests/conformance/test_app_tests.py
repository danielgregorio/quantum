"""Conformance: `quantum test` and *.test.q files (SPEC section 12, TEST-1..TEST-4, ROUTE-4)."""

import sqlite3
import textwrap

import pytest

from quantum.core.features.native_testing.src import TestParseError, parse_test_source
from quantum.runtime.app_testing import run_tests

MIGRATION = """
CREATE TABLE lists (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL);
CREATE TABLE items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    size TEXT NOT NULL CHECK (size IN ('small', 'large')),
    amount INTEGER NOT NULL,
    list_id INTEGER NOT NULL REFERENCES lists(id),
    note TEXT
);
INSERT INTO lists (name) VALUES ('Home');
"""

ITEMS = """<q:component name="Items">
  <q:action name="add" method="POST">
    <q:param name="title" required="true" minlength="3" />
    <q:query name="added" datasource="db">
      INSERT INTO items (title, size, amount, list_id) VALUES (:title, 'small', 1, 1)
      <q:param name="title" value="{title}" type="string" />
    </q:query>
    <q:redirect url="/?added=1" flash="Added: {title}" />
  </q:action>
  <q:set name="shown" value="{query.shown}" default="all" />
  <q:query name="items" datasource="db">SELECT title FROM items ORDER BY id</q:query>
  <p>Count: {items_result.recordCount}</p>
  <p>Hello {session.userName}</p>
  <q:loop query="items"><p>Item {items.title}</p></q:loop>
</q:component>
"""

BILL = """<q:component name="Bill">
  <q:set name="price" value="10" type="number" />
  <q:if condition="price">
    <q:set name="total" value="{price * query.qty}" type="number" />
  </q:if>
  <p>Total: {total}</p>
</q:component>
"""

PRIVATE = """<q:component name="Private" require_auth="true">
  <q:action name="wipe" method="POST">
    <q:query name="gone" datasource="db">DELETE FROM items</q:query>
    <q:redirect url="/private" />
  </q:action>
  <p>Private for {session.userName} ({session.userRole}), plan {session.plan}</p>
</q:component>
"""


def make_app(tmp_path, tests, pages=None, config=None, migration=MIGRATION, history=True):
    app = tmp_path / 'app'
    (app / 'components').mkdir(parents=True)
    (app / 'migrations').mkdir()
    (app / 'tests').mkdir()
    (app / 'migrations' / 'V001_items.sql').write_text(migration, encoding='utf-8')
    pages = {'index': ITEMS, 'bill': BILL, 'private': PRIVATE, 'login': '<q:component name="L"><p>Sign in</p></q:component>',
             **(pages or {})}
    for name, source in pages.items():
        (app / 'components' / f'{name}.q').write_text(source, encoding='utf-8')
    (app / 'quantum.config.yaml').write_text(config or (
        'server:\n  debug: false\n'
        'datasources:\n  db:\n    driver: sqlite\n    database: ./data/app.db\n'
        + ('    history: true\n' if history else '')), encoding='utf-8')
    for path, source in tests.items():
        target = app / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(textwrap.dedent(source), encoding='utf-8')
    return app


def run(*paths):
    lines = []
    code = run_tests([str(p) for p in paths], out=lines.append)
    return code, '\n'.join(lines)


# -- TEST-1 -------------------------------------------------------------------

class TestFindingAndRunning:
    def test_finds_tests_next_to_the_pages_and_in_tests(self, tmp_path):
        # TEST-1: components/ and tests/ are both searched; exit 0 when all pass
        app = make_app(tmp_path, {
            'components/index.test.q': '<q:test name="a"><test:visit/><test:expect text="Count: 0"/></q:test>',
            'tests/more.test.q': '<q:test name="b"><test:visit/><test:expect text="Count: 0"/></q:test>',
        })
        code, out = run(app)
        assert code == 0, out
        assert '2 passed, 0 failed' in out
        assert 'index.test.q' in out and 'more.test.q' in out

    def test_a_failure_exits_with_1_and_points_at_the_step(self, tmp_path):
        # TEST-1: the report names the test file and the line of the failing step
        app = make_app(tmp_path, {'tests/t.test.q': (
            '<q:test name="counts">\n'
            '  <test:visit/>\n'
            '  <test:expect text="Count: 9"/>\n'
            '</q:test>\n')})
        code, out = run(app)
        assert code == 1
        assert 'FAIL  counts' in out
        assert 't.test.q:3  <test:expect text="Count: 9"/>' in out
        assert 'expected the page (/) to show "Count: 9"' in out

    def test_each_test_gets_a_fresh_database(self, tmp_path):
        # TEST-1: what one test writes, the next one does not see
        app = make_app(tmp_path, {'tests/t.test.q': """
            <q:test name="writes">
              <test:submit action="add" title="Bread"/>
              <test:expect table="items" count="1"/>
            </q:test>
            <q:test name="starts clean">
              <test:expect table="items" count="0"/>
              <test:expect table="lists" count="1" where="name = 'Home'"/>
            </q:test>
            """})
        code, out = run(app)
        assert code == 0, out

    def test_the_apps_own_folder_and_database_are_not_touched(self, tmp_path):
        # TEST-1: a temporary database, even when the app's own database exists
        app = make_app(tmp_path, {'tests/t.test.q': """
            <q:test name="writes">
              <test:visit/>
              <test:submit action="add" title="Bread"/>
            </q:test>
            """})
        (app / 'data').mkdir()
        with sqlite3.connect(app / 'data' / 'app.db') as db:
            db.execute('CREATE TABLE marker (x)')
        before = sorted(p.relative_to(app).as_posix() for p in app.rglob('*'))
        code, out = run(app)
        assert code == 0, out
        after = sorted(p.relative_to(app).as_posix() for p in app.rglob('*') if '__pycache__' not in p.parts)
        assert after == before                          # no static/, logs/ or database written
        with sqlite3.connect(app / 'data' / 'app.db') as db:
            assert [r[0] for r in db.execute("SELECT name FROM sqlite_master")] == ['marker']

    def test_a_server_error_fails_at_the_step_with_the_pages_line(self, tmp_path):
        # TEST-1 + DEV-2: the step's line and the page's line
        app = make_app(tmp_path, {'tests/t.test.q': (
            '<q:test name="bill" page="/bill">\n'
            '  <test:visit/>\n'
            '  <test:expect text="Total"/>\n'
            '</q:test>\n')})
        code, out = run(app)
        assert code == 1
        assert 't.test.q:2  <test:visit/>' in out
        assert 'the server answered 500' in out
        assert 'bill.q:4' in out                        # the q:set that failed

    def test_an_expected_error_status_is_not_a_failure(self, tmp_path):
        # TEST-1: an error answer the next test:expect status asks for
        app = make_app(tmp_path, {'tests/t.test.q': """
            <q:test name="missing page">
              <test:visit path="/nowhere"/>
              <test:expect status="404"/>
            </q:test>
            <q:test name="missing action">
              <test:submit action="nope"/>
            </q:test>
            """})
        code, out = run(app)
        assert 'PASS  missing page' in out
        assert "FAIL  missing action" in out and "the page ran q:action \"add\", not \"nope\"" in out

    def test_nothing_to_run_is_an_error(self, tmp_path):
        # TEST-1: no test found, a path that does not exist, a file that does not parse
        app = make_app(tmp_path, {})
        assert run(app)[0] == 1
        assert run(tmp_path / 'nope')[0] == 1
        (app / 'tests' / 'bad.test.q').write_text('<q:test name="x"><test:click text="a"/></q:test>',
                                                  encoding='utf-8')
        code, out = run(app)
        assert code == 1 and 'test:click' in out and 'ERROR' in out

    def test_a_test_file_needs_an_app(self, tmp_path):
        # TEST-1: the nearest quantum.config.yaml above the file
        (tmp_path / 'lonely.test.q').write_text('<q:test name="x"><test:visit/></q:test>', encoding='utf-8')
        code, out = run(tmp_path / 'lonely.test.q')
        assert code == 1 and 'no quantum.config.yaml' in out

    def test_several_datasources_with_migrations_is_ambiguous(self, tmp_path):
        # TEST-1
        app = make_app(tmp_path, {'tests/t.test.q': '<q:test name="x"><test:visit/></q:test>'}, config=(
            'datasources:\n  db:\n    driver: sqlite\n    database: ./a.db\n'
            '  other:\n    driver: sqlite\n    database: ./b.db\n'))
        code, out = run(app)
        assert code == 1 and 'several datasources' in out

    def test_migrations_without_a_datasource(self, tmp_path):
        # TEST-1
        app = make_app(tmp_path, {'tests/t.test.q': '<q:test name="x"><test:visit/></q:test>'},
                       config='server:\n  debug: false\n')
        code, out = run(app)
        assert code == 1 and 'declares no datasource for them to build' in out

    def test_only_sqlite(self, tmp_path):
        # TEST-1
        app = make_app(tmp_path, {'tests/t.test.q': '<q:test name="x"><test:visit/></q:test>'}, config=(
            'datasources:\n  db:\n    driver: postgres\n    database: shop\n'))
        code, out = run(app)
        assert code == 1 and 'supports only sqlite' in out


# -- TEST-2 -------------------------------------------------------------------

class TestGiven:
    def test_required_columns_get_generated_values(self, tmp_path):
        # TEST-2: title (text), size (CHECK IN), amount (integer), list_id (FK) are generated
        app = make_app(tmp_path, {'tests/t.test.q': """
            <q:test name="generated">
              <test:given table="items"/>
              <test:expect table="items" count="1"
                           where="title = 'title 1' AND size = 'small' AND amount = 2 AND list_id = 1 AND note IS NULL"/>
            </q:test>
            """})
        code, out = run(app)
        assert code == 0, out

    @pytest.mark.parametrize('given,message', [
        ('table="nope"', 'no table "nope"'),
        ('table="items" colour="red"', 'has no column "colour"'),
        ('table="items" size="huge"', 'does not accept "huge": it is one of small, large'),
        ('table="items" amount="many"', '"many" is not an integer'),
        ('table="items" list_id="7"', 'there is no such row'),
    ])
    def test_a_value_the_schema_rejects_fails_the_step(self, tmp_path, given, message):
        # TEST-2
        app = make_app(tmp_path, {'tests/t.test.q': f'<q:test name="x"><test:given {given}/></q:test>'})
        code, out = run(app)
        assert code == 1 and message in out, out

    def test_a_foreign_key_with_nothing_to_point_at(self, tmp_path):
        # TEST-2
        app = make_app(tmp_path, {'tests/t.test.q': '<q:test name="x"><test:given table="items"/></q:test>'},
                       migration=MIGRATION.replace("INSERT INTO lists (name) VALUES ('Home');", ''))
        code, out = run(app)
        assert code == 1 and 'add a test:given for lists first' in out


# -- TEST-3 -------------------------------------------------------------------

class TestRequests:
    def test_submit_takes_the_browser_path_and_follows_the_redirect(self, tmp_path):
        # TEST-3: rules, redirect, flash; then the test is on the page it ended at
        app = make_app(tmp_path, {'tests/t.test.q': """
            <q:test name="add">
              <test:submit action="add" title="Bread"/>
              <test:expect status="302" redirect="/?added=1" flash="Added: Bread"/>
              <test:expect text="Item Bread"/>
              <test:expect var="shown" value="all"/>
              <test:submit action="add" title="Milk"/>
              <test:expect table="items" count="2"/>
            </q:test>
            <q:test name="rules">
              <test:submit action="add" title="x"/>
              <test:expect error="title" message="Must be at least 3 characters"/>
              <test:expect table="items" count="0"/>
            </q:test>
            """})
        code, out = run(app)
        assert code == 0, out

    def test_guards_apply_and_as_signs_in(self, tmp_path):
        # TEST-3: require_auth covers the action; test:as sets the session
        app = make_app(tmp_path, {'tests/t.test.q': """
            <q:test name="no session" page="/private">
              <test:given table="items"/>
              <test:submit action="wipe"/>
              <test:expect redirect="/login"/>
              <test:expect table="items" count="1"/>
            </q:test>
            <q:test name="signed in" page="/private">
              <test:as user="Ana" role="admin" plan="pro"/>
              <test:visit/>
              <test:expect text="Private for Ana (admin), plan pro"/>
            </q:test>
            """})
        code, out = run(app)
        assert code == 0, out

    def test_visit_passes_the_query_string(self, tmp_path):
        # TEST-3
        app = make_app(tmp_path, {'tests/t.test.q': """
            <q:test name="query">
              <test:visit shown="mine"/>
              <test:expect var="shown" value="mine"/>
            </q:test>
            """})
        assert run(app)[0] == 0

    def test_history_is_recorded_with_the_user(self, tmp_path):
        # TEST-3 + TEST-4: the submit goes through history (DB-11)
        app = make_app(tmp_path, {'tests/t.test.q': """
            <q:test name="history">
              <test:as user="ana"/>
              <test:submit action="add" title="Bread"/>
              <test:expect history="items" action="add" op="insert" user="ana" count="1"/>
              <test:expect history="items" where="title = 'Bread'"/>
            </q:test>
            """})
        code, out = run(app)
        assert code == 0, out


# -- TEST-4 -------------------------------------------------------------------

class TestExpect:
    @pytest.mark.parametrize('expect,message', [
        ('status="200"', 'expected status 200, got 302'),
        ('redirect="/"', 'expected a redirect to /, got /?added=1'),
        ('flash="Added"', 'expected flash "Added", got "Added: Bread"'),
        ('no-text="Item Bread"', 'not to show "Item Bread"'),
        ('error="title"', 'the submit was accepted'),
        ('var="shown" value="mine"', 'expected shown = "mine", got "all"'),
        ('var="nothing" value="1"', 'no variable "nothing"'),
        ('queries="0"', 'expected 0 queries in POST /, it ran 1'),
        ('table="items" count="5"', 'expected 5 rows in "items", found 1'),
        ('table="items" where="title = \'Milk\'"', 'found none'),
        ('history="items" op="delete"', 'history entries of "items" (op=delete), found none'),
    ])
    def test_each_assertion_fails_when_it_does_not_hold(self, tmp_path, expect, message):
        # TEST-4
        app = make_app(tmp_path, {'tests/t.test.q': f"""
            <q:test name="x">
              <test:submit action="add" title="Bread"/>
              <test:expect {expect}/>
            </q:test>
            """})
        code, out = run(app)
        assert code == 1 and message in out, out

    def test_queries_at_most(self, tmp_path):
        # TEST-4: counted by the /_dev recorder, whatever server.debug says
        app = make_app(tmp_path, {'tests/t.test.q': """
            <q:test name="x">
              <test:visit/>
              <test:expect queries="at most 1"/>
            </q:test>
            """})
        assert run(app)[0] == 0

    def test_an_assertion_about_a_request_before_any_request(self, tmp_path):
        # TEST-4
        app = make_app(tmp_path, {'tests/t.test.q': '<q:test name="x"><test:expect text="a"/></q:test>'})
        code, out = run(app)
        assert code == 1 and 'nothing was requested yet' in out

    def test_history_needs_history_on(self, tmp_path):
        # TEST-4
        app = make_app(tmp_path, {'tests/t.test.q': '<q:test name="x"><test:expect history="items"/></q:test>'},
                       history=False)
        code, out = run(app)
        assert code == 1 and 'does not record history' in out


class TestTheVocabulary:
    @pytest.mark.parametrize('source,message', [
        ('<q:test name="a"><test:click text="x"/></q:test>', '<test:click> is not a test step'),
        ('<q:test name="a"><q:set name="x" value="1"/></q:test>', '<q:set> is not a test step'),
        ('<q:test name="a"><test:expect colour="red"/></q:test>', 'has no assertion colour'),
        ('<q:test name="a"><test:expect/></q:test>', 'asserts nothing'),
        ('<q:test name="a"><test:expect count="1"/></q:test>', 'belongs to table or history'),
        ('<q:test name="a"><test:expect message="x"/></q:test>', 'belongs to error'),
        ('<q:test name="a"><test:expect table="t" history="t"/></q:test>', 'write one test:expect for each'),
        ('<q:test name="a"><test:expect var="x"/></q:test>', 'needs value'),
        ('<q:test name="a"><test:expect status="ok"/></q:test>', 'a status is a number'),
        ('<q:test name="a"><test:expect queries="few"/></q:test>', '"at most N"'),
        ('<q:test name="a"><test:expect history="t" op="merge"/></q:test>', 'op is one of'),
        ('<q:test name="a" screens="web"><test:visit/></q:test>', 'no attribute screens'),
        ('<q:test><test:visit/></q:test>', 'needs a name'),
        ('<q:test name="a"/>', 'has no steps'),
        ('<q:test name="a"><test:visit/></q:test><q:test name="a"><test:visit/></q:test>', 'two tests are called'),
        ('<q:test name="a">hi<test:visit/></q:test>', 'text inside'),
        ('<q:test name="a"><test:visit><x/></test:visit></q:test>', 'no content'),
        ('<q:test name="a"><test:submit title="x"/></q:test>', 'needs action'),
        ('<q:test name="a"><test:given name="x"/></q:test>', 'needs table'),
        ('<q:component name="c"/>', 'only <q:test> is allowed'),
        ('', 'no <q:test>'),
    ])
    def test_anything_outside_the_vocabulary_is_a_parse_error(self, source, message):
        # TEST-4 (PARSE-3)
        with pytest.raises(TestParseError) as error:
            parse_test_source(source, 'x.test.q')
        assert message in str(error.value)

    def test_a_parse_error_names_the_line(self):
        # TEST-4 (DEV-2)
        with pytest.raises(TestParseError) as error:
            parse_test_source('<q:test name="a">\n  <test:visit/>\n  <test:expect colour="red"/>\n</q:test>')
        assert error.value.line == 3
        assert 'at line 3: <test:expect colour="red"/>' in str(error.value)

    def test_several_tests_and_comments_need_no_root(self):
        # TEST-4
        suite = parse_test_source('<?xml version="1.0"?>\n<!-- a -->\n<q:test name="a"><test:visit/></q:test>\n'
                                  '<q:test name="b" page="/x"><test:submit action="go" id="1"/></q:test>')
        assert [(t.name, t.page, t.line) for t in suite.tests] == [('a', '/', 3), ('b', '/x', 4)]
        assert suite.tests[1].steps[0].attrs == {'action': 'go', 'id': '1'}


# -- ROUTE-4 --------------------------------------------------------------------

class TestTestFilesAreNotPages:
    def test_a_test_file_is_not_served(self, tmp_path, monkeypatch):
        # ROUTE-4
        app = make_app(tmp_path, {
            'components/index.test.q': '<q:test name="a"><test:visit/></q:test>',
            'components/item/[id].test.q': '<q:test name="b"><test:visit/></q:test>',
        })
        monkeypatch.chdir(app)
        from quantum.runtime.web_server import QuantumWebServer
        server = QuantumWebServer(str(app / 'quantum.config.yaml'))
        client = server.app.test_client()
        assert client.get('/index.test').status_code == 404
        assert client.get('/index.test.q').status_code == 404
        assert [r.file_path.name for r in server._dynamic_routes] == []

    def test_quantum_check_reads_it_as_a_test_file(self, tmp_path):
        # ROUTE-4
        from quantum.cli.check import ProjectChecker
        app = make_app(tmp_path, {
            'components/index.test.q': '<q:test name="a"><test:visit/></q:test>',
            'components/bad.test.q': '<q:test name="a">\n<test:hover/></q:test>',
        })
        problems = ProjectChecker(app, app / 'quantum.config.yaml').run()
        shown = [str(p) for p in problems]
        assert len(shown) == 1 and 'components/bad.test.q:2' in shown[0] and 'test:hover' in shown[0], shown
