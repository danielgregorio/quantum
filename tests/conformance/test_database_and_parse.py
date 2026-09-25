"""Conformance: SPEC.md sections 0 (Parse) and 5a (Database)."""

import sqlite3

import pytest

from quantum.core.parser import QuantumParser, QuantumParseError


def parse(body):
    return QuantumParser().parse(
        f'<q:component name="C" xmlns:q="https://quantum.lang/ns">{body}</q:component>')


class TestUnknownTags:
    @pytest.mark.parametrize('body,suggestion', [
        ('<q:sett name="x" value="1"/>', '<q:set>'),
        ('<q:loop type="range" var="i" from="1" to="2"><q:retrun value="{i}"/></q:loop>', '<q:return>'),
        ('<div><q:lopp type="range" var="i" from="1" to="2"/></div>', '<q:loop>'),
    ])
    def test_an_error_with_a_suggestion_in_any_body(self, body, suggestion):
        # PARSE-1 (before: silently dropped, and the program went on without it)
        with pytest.raises(QuantumParseError, match=rf'is not a Quantum tag \(PARSE-1\)\. Did you mean {suggestion}'):
            parse(body)

    @pytest.mark.parametrize('tag', ['q:try', 'q:storedproc', 'q:fetch', 'q:include', 'q:throw'])
    def test_tags_the_docs_promised_and_never_existed(self, tag):
        # PARSE-1
        with pytest.raises(QuantumParseError, match='is not a Quantum tag'):
            parse(f'<{tag} name="x"/>')

    def test_other_namespaces_and_html_are_not_affected(self):
        # PARSE-1
        parse('<section><custom-element>x</custom-element></section>')

    def test_q_script_is_a_language_tag(self):
        # PARSE-1: the one HTML name with the prefix that is a tag of the language
        parse('<q:script>console.log(1)</q:script>')

    @pytest.mark.parametrize('tag', ['html', 'div', 'span'])
    def test_an_html_element_with_the_q_prefix_is_an_error(self, tag):
        # PARSE-1 (before: <q:html value="{x}"/> became an empty <html>)
        with pytest.raises(QuantumParseError, match=f'<q:{tag}> is not a Quantum tag'):
            parse(f'<q:{tag} value="1"/>')


class TestTheHtmlPeopleWrite:
    @pytest.mark.parametrize('body', [
        '<form><input name="q" required></form>',
        '<p>Forms & Actions <a href="/x?a=1&b=2">x</a></p>',
        '<p>a<br>b</p>',
        '<q:set name="n" value="1"/><q:if condition="n < 0"><p>neg</p></q:if>',
        '<q:set name="b" value="{1 < 2}"/>',
        '<p>a&nbsp;b &copy;</p>',
    ])
    def test_it_parses(self, body):
        # PARSE-4
        parse(body)

    def test_an_entity_that_does_not_exist_is_an_error(self):
        # PARSE-4
        with pytest.raises(Exception):
            parse('<p>&doesNotExistAtAll;</p>')


class TestStatementInMarkup:
    @pytest.mark.parametrize('body,fragment', [
        ('<ul><q:set name="y" value="1"/><li>{y}</li></ul>', '<q:set name="y"> inside <ul>'),
        ('<div><q:if condition="1 == 1"><q:query name="r" datasource="db">SELECT 1</q:query></q:if></div>',
         '<q:query name="r"> inside <div>'),
        ('<section><q:action name="save"><q:set name="x" value="1"/></q:action></section>',
         '<q:action name="save"> inside <section>'),
    ])
    def test_a_statement_inside_an_element_is_an_error(self, body, fragment):
        # PARSE-2 (before: it never ran; <li>{y}</li> came out literal and the action was never found)
        with pytest.raises(QuantumParseError, match='never runs') as error:
            parse(body)
        assert fragment in str(error.value)

    def test_a_statement_in_a_component_call_content_is_an_error(self):
        # PARSE-2
        with pytest.raises(QuantumParseError, match='inside the content of <Layout>'):
            parse('<q:import component="Layout"/><Layout><q:set name="y" value="1"/><p>{y}</p></Layout>')

    @pytest.mark.parametrize('row', ['<p>{y}</p>', '<q:if condition="y &gt; 1"><p>a</p></q:if>',
                                     '<span title="{y}">a</span>'])
    def test_a_loop_value_read_by_the_rows_is_an_error(self, row):
        # PARSE-2 (before: every row showed the value of the last iteration)
        with pytest.raises(QuantumParseError, match='every row would show the last value'):
            parse('<q:set name="xs" type="array" value="[1, 2, 3]"/>'
                  f'<q:loop type="array" items="{{xs}}" var="x"><q:set name="y" value="{{x * 2}}"/>{row}</q:loop>')

    def test_what_still_works(self, run_body):
        # PARSE-2: a total read after the loop, a top-level q:if, and the same field with another owner (x.y)
        parse('<q:set name="xs" type="array" value="[1, 2]"/>'
              '<q:loop type="array" items="{xs}" var="x"><q:set name="total" operation="increment"/>'
              '<li>{x}</li></q:loop><p>{total}</p>'
              '<q:if condition="1 == 1"><q:set name="z" value="1"/><p>{z}</p></q:if>'
              '<q:loop type="array" items="{xs}" var="x"><q:set name="y" value="1"/><p>{x.y}</p></q:loop>')
        assert run_body('<q:set name="xs" type="array" value="[1, 2, 3]"/>'
                        '<q:loop type="array" items="{xs}" var="x"><q:set name="total" operation="increment"/></q:loop>'
                        '<q:return value="{total}"/>') == 3


@pytest.fixture
def db(tmp_path):
    path = tmp_path / 'app.db'
    connection = sqlite3.connect(path)
    connection.executescript(
        "create table users (id integer primary key, name text, status text);"
        "insert into users (name, status) values ('Ana','active'),('Bia','active'),('Caio','inactive');"
        "create table products (id integer primary key, stock integer);"
        "insert into products (stock) values (10);")
    connection.commit()
    connection.close()
    return path


@pytest.fixture
def run_db(db, tmp_path):
    import contextlib
    import io
    from quantum.runtime.component import ComponentRuntime

    def run(body):
        path = tmp_path / 'q.q'
        path.write_text(f'<q:component name="Q" xmlns:q="https://quantum.lang/ns">{body}</q:component>',
                        encoding='utf-8')
        config = {'datasources': {'db': {'driver': 'sqlite', 'database': str(db)}}}
        with contextlib.redirect_stdout(io.StringIO()):
            return ComponentRuntime(config=config).execute_component(
                QuantumParser().parse_file(str(path)), {})
    return run


class TestQueries:
    def test_parameters_and_result(self, run_db):
        # DB-1
        r = run_db('<q:query name="u" datasource="db">SELECT name FROM users WHERE status = :s ORDER BY id'
                   '<q:param name="s" value="active" type="string"/></q:query>'
                   '<q:return value="{u_result}"/>')
        assert r['data'] == [{'name': 'Ana'}, {'name': 'Bia'}]
        assert r['success'] is True and r['recordCount'] == 2 and r['columnList'] == ['name']

    def test_one_row_exposes_its_fields(self, run_db):
        # DB-1
        assert run_db('<q:query name="u" datasource="db">SELECT name FROM users WHERE id = 1</q:query>'
                      '<q:return value="{u.name}"/>') == 'Ana'

    def test_a_write_reports_the_affected_rows(self, run_db):
        # DB-1
        assert run_db('<q:query name="up" datasource="db">UPDATE users SET status = :s WHERE status = :v'
                      '<q:param name="s" value="x" type="string"/><q:param name="v" value="active" type="string"/>'
                      '</q:query><q:return value="{up_result.affectedRows}"/>') == 2

    def test_a_name_without_a_param_is_a_parse_error(self):
        # DB-1
        with pytest.raises(QuantumParseError, match=r':id declared in SQL but no matching <q:param>'):
            parse('<q:query name="u" datasource="db">SELECT * FROM users WHERE id = :id</q:query>')

    def test_an_insert_reports_the_new_id_and_result_renames_the_object(self, run_db):
        # DB-1
        r = run_db('<q:query name="i" datasource="db" result="saved">'
                   'INSERT INTO users (name, status) VALUES (:n, :s)'
                   '<q:param name="n" value="Dora"/><q:param name="s" value="new"/></q:query>'
                   '<q:return value="{saved}"/>')
        assert r['success'] is True and r['affectedRows'] == 1 and r['lastInsertId'] == 4
        assert isinstance(r['executionTime'], (int, float))

    def test_pagination(self, run_db):
        # DB-2
        r = run_db('<q:query name="p" datasource="db" paginate="true" page="2" page_size="2">'
                   'SELECT name FROM users ORDER BY id</q:query><q:return value="{p_result.pagination}"/>')
        assert (r['totalRecords'], r['totalPages'], r['currentPage'], r['hasNextPage'], r['hasPreviousPage']) == \
            (3, 2, 2, False, True)
        assert (r['pageSize'], r['startRecord'], r['endRecord']) == (2, 3, 3)

    def test_query_of_queries(self, run_db):
        # DB-3
        assert run_db('<q:query name="everyone" datasource="db">SELECT name, status FROM users</q:query>'
                      '<q:query name="active" source="everyone">SELECT name FROM everyone WHERE status = \'active\' '
                      'ORDER BY name</q:query><q:return value="{active}"/>') == [{'name': 'Ana'}, {'name': 'Bia'}]

    def test_a_transaction_inherits_the_datasource_and_rolls_back_on_failure(self, run_db):
        # DB-4 (before: a query without a datasource inside the transaction did not parse)
        with pytest.raises(Exception, match='rolled back'):
            run_db('<q:transaction datasource="db">'
                   '<q:query name="a">UPDATE products SET stock = 999 WHERE id = 1</q:query>'
                   '<q:query name="b">INSERT INTO missing VALUES (1)</q:query></q:transaction>')
        assert run_db('<q:query name="s" datasource="db">SELECT stock FROM products</q:query>'
                      '<q:return value="{s.stock}"/>') == 10

    def test_queries_nested_in_a_loop_or_an_if_inherit_it_too(self, run_db):
        # DB-4 (before: a q:query inside q:loop or q:if inside the transaction
        # had to repeat datasource=, or it did not parse)
        with pytest.raises(Exception, match='rolled back'):
            run_db('<q:transaction datasource="db">'
                   '<q:loop items="{[1, 2]}" var="i">'
                   '<q:if condition="i == 1">'
                   '<q:query name="a">UPDATE products SET stock = 999 WHERE id = 1</q:query></q:if>'
                   '<q:query name="b">INSERT INTO missing VALUES (:i)'
                   '<q:param name="i" value="{i}" type="integer"/></q:query>'
                   '</q:loop></q:transaction>')
        assert run_db('<q:query name="s" datasource="db">SELECT stock FROM products</q:query>'
                      '<q:return value="{s.stock}"/>') == 10

    def test_a_nested_query_keeps_the_datasource_it_names(self):
        # DB-4: inheriting never overrides what a query declares
        node = next(s for s in parse('<q:transaction datasource="db"><q:loop items="{[1]}" var="i">'
                                     '<q:query name="a" datasource="other">SELECT 1</q:query>'
                                     '</q:loop></q:transaction>').statements
                    if type(s).__name__ == 'TransactionNode')
        loop = node.statements[0]
        query = next(s for s in getattr(loop, 'body', None) or loop.statements
                     if type(s).__name__ == 'QueryNode')
        assert query.datasource == 'other'

    @pytest.mark.parametrize('declared,level', [('', 'READ_COMMITTED'),
                                                 ('isolationLevel="SERIALIZABLE"', 'SERIALIZABLE'),
                                                 ('isolation="REPEATABLE_READ"', 'REPEATABLE_READ')])
    def test_a_transaction_keeps_its_level_and_datasource(self, declared, level):
        # DB-4 (before: every q:transaction failed validation with "Invalid
        # isolation level: ", and datasource= never reached the node)
        node = next(s for s in parse(f'<q:transaction datasource="db" {declared}>'
                                     '<q:query name="a">SELECT 1</q:query></q:transaction>').statements
                    if type(s).__name__ == 'TransactionNode')
        assert (node.isolation_level, node.datasource, node.validate()) == (level, 'db', [])

    def test_an_unknown_isolation_level_is_a_parse_error(self):
        # DB-4
        with pytest.raises(QuantumParseError, match='SERIALIZABLE'):
            parse('<q:transaction datasource="db" isolationLevel="SERIAL">'
                  '<q:query name="a">SELECT 1</q:query></q:transaction>')

    @pytest.mark.parametrize('attribute', ['cache="true"', 'ttl="60"', 'reactive="true"', 'interval="5"',
                                           'timeout="3"', 'maxrows="1"', 'batch="true"'])
    def test_attributes_that_never_worked(self, attribute):
        # DB-5
        with pytest.raises(QuantumParseError, match='is not supported'):
            parse(f'<q:query name="x" datasource="db" {attribute}>SELECT 1</q:query>')


class TestMigrations:
    def project(self, tmp_path, config):
        (tmp_path / 'quantum.config.yaml').write_text(config, encoding='utf-8')
        (tmp_path / 'migrations').mkdir()
        (tmp_path / 'migrations' / 'V001_users.sql').write_text(
            'CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);', encoding='utf-8')
        return tmp_path

    def test_applies_to_the_declared_datasource(self, tmp_path):
        # DB-6 (before: it went to ./data/quantum.db, or to any local PostgreSQL)
        from quantum.cli.migrations import MigrationRunner
        project = self.project(tmp_path, 'datasources:\n  db:\n    driver: sqlite\n    database: ./data/app.db\n')
        MigrationRunner(project_path=project).up()
        tables = sqlite3.connect(project / 'data' / 'app.db').execute(
            "select name from sqlite_master where type='table'").fetchall()
        assert ('users',) in tables
        assert not (project / 'data' / 'quantum.db').exists()

    def test_several_datasources_need_a_choice(self, tmp_path):
        # DB-6
        from quantum.cli.migrations import MigrationError, MigrationRunner
        project = self.project(tmp_path, 'datasources:\n  a:\n    driver: sqlite\n    database: a.db\n'
                                         '  b:\n    driver: sqlite\n    database: b.db\n')
        with pytest.raises(MigrationError, match='--datasource'):
            MigrationRunner(project_path=project).up()
        MigrationRunner(project_path=project, datasource='b').up()
        assert (project / 'b.db').exists() and not (project / 'a.db').exists()

    def test_a_file_with_several_statements_is_atomic(self, tmp_path):
        # DB-8 (before: "You can only execute one statement at a time" on every real migration)
        from quantum.cli.migrations import MigrationRunner
        project = self.project(tmp_path, 'datasources:\n  db:\n    driver: sqlite\n    database: app.db\n')
        (project / 'migrations' / 'V002_more.sql').write_text(
            "-- a table and an index\nCREATE TABLE posts (id INTEGER PRIMARY KEY, t TEXT);\n"
            "CREATE INDEX idx_t ON posts(t);\nINSERT INTO posts (t) VALUES ('a; b');\n", encoding='utf-8')
        (project / 'migrations' / 'V003_broken.sql').write_text(
            "CREATE TABLE a (x INT);\nCREATE TABLE b (;\n", encoding='utf-8')
        result = [r['status'] for r in MigrationRunner(project_path=project).up()]
        assert result == ['applied', 'applied', 'failed']
        db = sqlite3.connect(project / 'app.db')
        assert db.execute('select t from posts').fetchall() == [('a; b',)]
        # the one that failed halfway does not leave its first table behind
        assert db.execute("select count(*) from sqlite_master where name = 'a'").fetchone()[0] == 0


class TestDeclaredDatasource:
    def _run(self, tmp_path, config, body):
        import contextlib
        import io
        from quantum.runtime.component import ComponentRuntime
        path = tmp_path / 'q.q'
        path.write_text(f'<q:component name="Q" xmlns:q="https://quantum.lang/ns">{body}</q:component>',
                        encoding='utf-8')
        with contextlib.redirect_stdout(io.StringIO()):
            return ComponentRuntime(config=config).execute_component(QuantumParser().parse_file(str(path)), {})

    def test_a_sqlite_file_that_does_not_exist_is_an_error_and_is_not_created(self, tmp_path):
        # DB-7 (before: sqlite3 created an empty database and the error was "no such table")
        missing = tmp_path / 'missing.db'
        with pytest.raises(Exception, match='does not exist.*quantum migrate up'):
            self._run(tmp_path, {'datasources': {'db': {'driver': 'sqlite', 'database': str(missing)}}},
                      '<q:query name="r" datasource="db">SELECT 1</q:query>')
        assert not missing.exists()

    def test_an_undeclared_datasource_is_an_immediate_error(self, tmp_path, monkeypatch):
        # DB-7 (before: a hidden HTTP call to localhost:8000, with a 5 s wait)
        import requests

        def forbidden(*a, **k):
            raise AssertionError('no network call')
        monkeypatch.setattr(requests, 'get', forbidden)
        with pytest.raises(Exception, match=r"'other' is not declared in quantum.config.yaml \(declared: db\)"):
            self._run(tmp_path, {'datasources': {'db': {'driver': 'sqlite', 'database': ':memory:'}}},
                      '<q:query name="r" datasource="other">SELECT 1</q:query>')

    def test_a_datasource_key_nothing_reads_is_warned_about(self, tmp_path):
        # DB-7: the blog declared sqlite_path:, which nothing read
        import logging
        from quantum.runtime.web_server import _validate_config
        records = []
        collector = logging.Handler(logging.WARNING)
        collector.emit = records.append
        logger = logging.getLogger('quantum')
        level = logger.level
        logger.setLevel(logging.WARNING)
        logger.addHandler(collector)
        try:
            _validate_config({'datasources': {'blog': {'driver': 'sqlite', 'database': 'x.db',
                                                       'sqlite_path': 'data/blog.db'}}}, 'cfg')
        finally:
            logger.removeHandler(collector)
            logger.setLevel(level)
        assert any('datasources.blog: sqlite_path is not read' in r.getMessage() for r in records)


class TestAcceptedWithoutEffect:
    @pytest.mark.parametrize('fragment,attribute', [
        ('<q:set name="x" value="1" mask="999"/>', 'mask'),
        ('<q:invoke name="r" url="http://x" transform="upper"/>', 'transform'),
        ('<q:function name="f"><q:param name="a" validation="email"/><q:return value="1"/></q:function>', 'validation'),
        ('<q:set name="x" value="1" unique="true"/>', 'unique'),
    ] + [(f'<q:data name="d" source="d.csv"><q:column name="c" {a}="1"/></q:data>', a)
         for a in ('required', 'default', 'validate', 'pattern', 'min', 'max', 'minlength', 'maxlength',
                   'range', 'enum')])
    def test_an_attribute_that_never_did_anything_is_an_error(self, fragment, attribute):
        # PARSE-3 (before: accepted and ignored)
        with pytest.raises(QuantumParseError, match=f'{attribute}= is not supported: it was accepted'):
            parse(fragment)

    @pytest.mark.parametrize('attribute', ['basePath="/x"', 'health="/h"', 'metrics="prom"', 'trace="otel"'])
    def test_a_component_attribute_that_never_did_anything_is_an_error(self, attribute):
        # PARSE-3
        with pytest.raises(QuantumParseError, match='is not supported: it was accepted'):
            QuantumParser().parse(f'<q:component name="c" {attribute} xmlns:q="https://quantum.lang/ns"><p>x</p></q:component>')


# ------------------------------------------------------------------ DB-1: the params' types

@pytest.mark.parametrize('param,message', [
    ('value="abc" type="integer"', "Parameter 'p' validation failed: Cannot convert 'abc' to integer"),
    ('value="abcdef" type="string" maxLength="3"', "Parameter 'p' validation failed: String length 6 exceeds maximum 3"),
    ('value="1" type="galaxy"', 'type="galaxy" does not exist'),       # PARSE-5: a parse error now
])
def test_a_param_that_does_not_convert_is_an_error(run_db, param, message):
    # DB-1
    with pytest.raises(Exception, match=message):
        run_db(f'<q:query name="u" datasource="db">SELECT :p AS p<q:param name="p" {param}/></q:query>')


def test_scale_rounds_a_decimal(run_db):
    # DB-1
    assert run_db('<q:query name="u" datasource="db">SELECT :p AS p<q:param name="p" value="1.23456" type="decimal" '
                  'scale="2"/></q:query><q:return value="{u.p}"/>') == 1.23


@pytest.mark.parametrize('param,expected', [('value="true" type="boolean"', 1), ('value="7" type="integer"', 7),
                                            ('value="2026-09-24" type="date"', '2026-09-24')])
def test_a_param_is_converted_before_it_is_bound(run_db, param, expected):
    # DB-1
    assert run_db(f'<q:query name="u" datasource="db">SELECT :p AS p<q:param name="p" {param}/></q:query>'
                  '<q:return value="{u.p}"/>') == expected
